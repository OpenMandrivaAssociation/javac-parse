Name:		javac-parse
Version:	1.0.0
Release:	1
Summary:	Wrapper around javac's parser
Group:		Development/Java
License:	GPL-2.0-only WITH Classpath-exception-2.0
URL:		https://github.com/plume-lib/javac-parse
# Tag v1.0.0, Java sources only. The Gradle wrapper jar is not in this archive.
# dataflow-nullaway 4.0.0 requires 0.9.0, so that jar stays installed.
Source0:	https://github.com/plume-lib/javac-parse/archive/refs/tags/v%{version}.tar.gz#/javac-parse-%{version}.tar.gz
Source1:	https://github.com/plume-lib/javac-parse/archive/refs/tags/v0.9.0.tar.gz#/javac-parse-0.9.0.tar.gz
# 1.0.0 makes JavacParseResult a record, whose accessor is tree().
# getTree() stays so jars built against 0.9.0 still link.
Patch0:		javac-parse-1.0.0-gettree.patch

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.checkerframework:checker-qual) = 4.4.0

%description
javac-parse %{version} calls the JDK javac parser and returns a tree.
Checker Framework dataflow uses it to parse Java expressions.
0.9.0 stays installed for dataflow-nullaway 4.0.0.
parseExpression(String) returns the tree. JavacParseResult keeps
getTree() so callers that still hold a result object can link.
The class files match the JDK that built them. GuardSatisfied comes
from checker-qual and is compile-only.

A caller in the unnamed module needs:
--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED

%prep
%autosetup -n javac-parse-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
test -f src/main/java/org/plumelib/javacparse/JavacParse.java
grep -q 'public T getTree()' src/main/java/org/plumelib/javacparse/JavacParseResult.java
tar -C %{_builddir} -xf %{SOURCE1}
find %{_builddir}/javac-parse-0.9.0 -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries-old.list
if [ -s binaries-old.list ]; then
	cat binaries-old.list
	exit 1
fi
test -f %{_builddir}/javac-parse-0.9.0/src/main/java/org/plumelib/javacparse/JavacParse.java

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
feature=$(java -XshowSettings:properties -version 2>&1 | awk -F= '/java.specification.version/{gsub(/ /,"",$2); print $2}')
major=$((feature + 44))
build_one() (
	dir="$1"
	ver="$2"
	cd "%{_builddir}/${dir}"
	find src/main/java -name '*.java' > sources.list
	test "$(wc -l < sources.list)" -eq 5
	mkdir -p classes
	javac -encoding UTF-8 -proc:none -Xlint:all,-processing,-options,-this-escape,-removal -Werror \
		--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED \
		--add-exports=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED \
		--add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED \
		--add-exports=jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED \
		--add-exports=jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED \
		--add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED \
		-cp %{_javadir}/checker-qual.jar \
		-d classes @sources.list
	echo 'Automatic-Module-Name: org.plumelib.javacparse' > javac-parse.mf
	jar cfm javac-parse.jar javac-parse.mf -C classes .
	jar i javac-parse.jar
	javap -v -classpath javac-parse.jar org.plumelib.javacparse.JavacParse | grep -F -q "major version: ${major}"
	javap -public -classpath javac-parse.jar org.plumelib.javacparse.JavacParseResult | grep -F -q 'getTree()'
	desc=$(jar --describe-module --file javac-parse.jar)
	printf '%s\n' "$desc" | grep -F -q 'org.plumelib.javacparse'
	if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
		exit 1
	fi
	cat > javac-parse.pom << EOF
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.plumelib</groupId>
  <artifactId>javac-parse</artifactId>
  <version>${ver}</version>
  <name>javac-parse</name>
  <description>Wrapper around javac's parser, used by Checker Framework dataflow.</description>
  <url>https://github.com/plume-lib/javac-parse</url>
  <licenses>
    <license>
      <name>GPL-2.0-only WITH Classpath-exception-2.0</name>
      <url>https://www.gnu.org/licenses/old-licenses/gpl-2.0.html</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
</project>
EOF
	grep -F -q "<version>${ver}</version>" javac-parse.pom
)
build_one javac-parse-0.9.0 0.9.0
build_one javac-parse-%{version} %{version}

%install
set -eo pipefail
old="%{_builddir}/javac-parse-0.9.0"
sysjar install --buildroot %{buildroot} \
	--artifact "${old}/javac-parse.pom:${old}/javac-parse.jar" \
	--file-name javac-parse-0.9.0 \
	--filelist .mfiles-old
index="%{buildroot}/usr/share/sysjar/index/org.plumelib/javac-parse.sysjar"
test -f "$index"
/bin/mv "$index" "%{buildroot}/usr/share/sysjar/index/org.plumelib/javac-parse-0.9.0.sysjar"
sed -i 's|/usr/share/sysjar/index/org\.plumelib/javac-parse\.sysjar|/usr/share/sysjar/index/org.plumelib/javac-parse-0.9.0.sysjar|' .mfiles-old
idx="%{buildroot}/usr/share/sysjar/index/org.plumelib/javac-parse-0.9.0.sysjar"
grep -F -q '"version": "0.9.0"' "$idx"
grep -F -q '"artifactId": "javac-parse"' "$idx"
new="%{_builddir}/javac-parse-%{version}"
sysjar install --buildroot %{buildroot} \
	--artifact "${new}/javac-parse.pom:${new}/javac-parse.jar" \
	--file-name javac-parse \
	--filelist .mfiles-new
idxn="%{buildroot}/usr/share/sysjar/index/org.plumelib/javac-parse.sysjar"
grep -F -q '"version": "%{version}"' "$idxn"
grep -F -q '"artifactId": "javac-parse"' "$idxn"
test -s %{buildroot}%{_javadir}/javac-parse-0.9.0.jar
test -s %{buildroot}%{_javadir}/javac-parse.jar
: > .mfiles
for list in .mfiles-old .mfiles-new
do
	while IFS= read -r line; do
		grep -qxF -- "$line" .mfiles || printf '%%s\n' "$line" >> .mfiles
	done < "$list"
done
grep -F -q '/javac-parse.jar' .mfiles
grep -F -q '/javac-parse-0.9.0.jar' .mfiles

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
mkdir -p check
cat > check/Smoke.java << 'EOF'
import com.sun.source.tree.BinaryTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.LiteralTree;
import org.plumelib.javacparse.JavacParse;
import org.plumelib.javacparse.JavacParseResult;

public class Smoke {
	public static void main(String[] args) {
		JavacParseResult<ExpressionTree> parsed = JavacParse.parseExpression(args[1]);
		if (parsed.hasParseError()) {
			throw new AssertionError(parsed.getParseErrorMessages());
		}
		ExpressionTree tree = parsed.getTree();
		if (!(tree instanceof BinaryTree)) {
			throw new AssertionError(tree.getKind());
		}
		BinaryTree binary = (BinaryTree) tree;
		String left = ((LiteralTree) binary.getLeftOperand()).getValue().toString();
		String right = ((LiteralTree) binary.getRightOperand()).getValue().toString();
		System.out.println(args[0] + " " + left + " " + binary.getKind() + " " + right);
	}
}
EOF
cat > check/SmokeNew.java << 'EOF'
import com.sun.source.tree.BinaryTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.LiteralTree;
import org.plumelib.javacparse.JavacParse;
import org.plumelib.javacparse.JavacParseResult;

public class SmokeNew {
	public static void main(String[] args) {
		ExpressionTree tree = JavacParse.parseExpression(args[1]);
		if (!(tree instanceof BinaryTree)) {
			throw new AssertionError(tree.getKind());
		}
		BinaryTree binary = (BinaryTree) tree;
		String left = ((LiteralTree) binary.getLeftOperand()).getValue().toString();
		String right = ((LiteralTree) binary.getRightOperand()).getValue().toString();
		JavacParseResult<CompilationUnitTree> unit = JavacParse.parseCompilationUnit("class C {}");
		if (unit.hasParseError()) {
			throw new AssertionError(unit.getParseErrorMessages());
		}
		CompilationUnitTree cu = unit.getTree();
		if (cu == null) {
			throw new AssertionError("null tree");
		}
		System.out.println(args[0] + " " + left + " " + binary.getKind() + " " + right + " " + cu.getKind());
	}
}
EOF
EXPORTS="--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED"
run_check() {
	label="$1"
	jar="$2"
	src="$3"
	main="$4"
	expect="$5"
	javac -encoding UTF-8 -proc:none $EXPORTS -cp "$jar" -d check "$src"
	java $EXPORTS -cp "check:$jar" "$main" "$label" '1 + 2' > "check/${label}.txt"
	cat "check/${label}.txt"
	grep -F -q "$expect" "check/${label}.txt"
}
run_check javacparse_ok_0.9.0 %{buildroot}%{_javadir}/javac-parse-0.9.0.jar check/Smoke.java Smoke 'javacparse_ok_0.9.0 1 PLUS 2'
run_check javacparse_ok_%{version} %{buildroot}%{_javadir}/javac-parse.jar check/SmokeNew.java SmokeNew 'javacparse_ok_%{version} 1 PLUS 2 COMPILATION_UNIT'

%files -f .mfiles
%doc README.md CHANGELOG.md
%license LICENSE
